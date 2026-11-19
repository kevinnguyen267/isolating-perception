(define (problem blocksworld)
	(:domain blocksworld)
	(:objects
		blue - block
		green - block
		orange - block
		purple - block
		red - block
		yellow - block
		robot - robot
	)
	(:init (handempty robot)
		(ontable purple)
		(on blue purple)
		(clear blue)
		(ontable red)
		(on orange red)
		(clear orange)

		(ontable yellow)
		(on green yellow)
		(clear green)
	)
	(:goal (and (handempty robot)
		(ontable yellow)
		(on green yellow)
		(on red green)
		(clear red)
		(ontable orange)
		(on blue orange)
		(clear blue)

		(ontable purple)
		(clear purple)
	))
)