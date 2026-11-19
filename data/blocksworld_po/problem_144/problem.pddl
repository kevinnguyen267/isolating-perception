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
		(ontable red)
		(on orange red)
		(on purple orange)
		(on blue purple)
		(clear blue)

		(ontable green)
		(clear green)
		(ontable yellow)
		(clear yellow)
	)
	(:goal (and (handempty robot)
		(ontable red)
		(clear red)
		(ontable orange)
		(clear orange)
		(ontable yellow)
		(clear yellow)
		(ontable green)
		(clear green)
		(ontable blue)
		(clear blue)
		(ontable purple)
		(clear purple)
	))
)