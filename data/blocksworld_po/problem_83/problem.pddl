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
		(ontable orange)
		(on blue orange)
		(on yellow blue)
		(clear yellow)
		(ontable red)
		(clear red)

		(ontable purple)
		(clear purple)
		(ontable green)
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