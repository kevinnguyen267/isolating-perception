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
		(on green purple)
		(clear green)

		(ontable red)
		(clear red)
		(ontable orange)
		(clear orange)
		(ontable yellow)
		(clear yellow)
		(ontable blue)
		(clear blue)
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